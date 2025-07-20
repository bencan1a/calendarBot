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
        
        console.log('SettingsPanel: Initialized with layout:', this.currentLayout, 'screen size:', this.screenSize);
    }

    /**
     * Initialize the settings panel system
     * Creates DOM elements, sets up event listeners, and initializes components
     */
    async initialize() {
        if (this.isInitialized) {
            console.warn('SettingsPanel: Already initialized');
            return;
        }

        try {
            // Create panel DOM structure
            this.createPanelHTML();
            
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
            console.log('SettingsPanel: Initialization complete');
            
        } catch (error) {
            console.error('SettingsPanel: Initialization failed:', error);
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

        const panelHTML = `
            <div id="settings-panel" class="settings-panel" role="dialog" aria-labelledby="settings-title" aria-hidden="true">
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
        console.log('SettingsPanel: Panel HTML created');
    }

    /**
     * Setup form event listeners
     */
    setupFormEventListeners() {
        const panel = document.getElementById('settings-panel');
        if (!panel) {
            console.error('SettingsPanel: Panel element not found during event setup');
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

        console.log('SettingsPanel: Form event listeners setup complete');
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
                this.currentSettings = result.data;
                this.localSettings = JSON.parse(JSON.stringify(result.data)); // Deep copy
                this.populateForm(this.localSettings);
                this.hideStatus();
                console.log('SettingsPanel: Settings loaded successfully');
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

        console.log('SettingsPanel: Form populated with settings');
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
                event_filters: { title_patterns: [] },
                display: {},
                metadata: {}
            };
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
                console.log('SettingsPanel: Settings saved successfully');
                
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

            // Load fresh settings
            await this.loadSettings();

            // Show panel
            panel.classList.add('open');
            panel.setAttribute('aria-hidden', 'false');
            
            // Focus management
            const firstFocusable = panel.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                setTimeout(() => firstFocusable.focus(), 100);
            }

            this.isOpen = true;
            this.isTransitioning = false;
            
            console.log('SettingsPanel: Panel opened');
            
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
            return;
        }

        this.isTransitioning = true;
        
        const panel = document.getElementById('settings-panel');
        if (panel) {
            // ACCESSIBILITY FIX: Manage focus before setting aria-hidden
            // Check if any element inside the panel currently has focus
            const focusedElement = document.activeElement;
            const panelContainsFocus = panel.contains(focusedElement);
            
            if (panelContainsFocus) {
                // Blur the focused element first to prevent accessibility violation
                if (focusedElement && typeof focusedElement.blur === 'function') {
                    focusedElement.blur();
                }
                
                // Move focus to a safe element outside the panel
                // Try to focus on the document body as a fallback
                if (document.body && typeof document.body.focus === 'function') {
                    document.body.focus();
                } else {
                    // Alternative: focus on the main content area if available
                    const mainContent = document.querySelector('main, .calendar-content, body');
                    if (mainContent && typeof mainContent.focus === 'function') {
                        mainContent.focus();
                    }
                }
            }
            
            // PANEL HIDING FIX: Remove all visibility-related classes and reset transform
            panel.classList.remove('open', 'revealing');
            panel.style.transform = '';
            panel.setAttribute('aria-hidden', 'true');
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
        
        console.log('SettingsPanel: Panel closed with proper focus and visibility management');
    }

    /**
     * Methods called by gesture handler
     */
    startReveal() {
        const panel = document.getElementById('settings-panel');
        if (panel) {
            panel.classList.add('revealing');
        }
    }

    updateReveal(percent) {
        const panel = document.getElementById('settings-panel');
        if (panel) {
            panel.style.transform = `translateY(${-100 + (percent * 100)}%)`;
        }
    }

    cancelReveal() {
        const panel = document.getElementById('settings-panel');
        if (panel) {
            panel.classList.remove('revealing');
            panel.style.transform = '';
        }
    }

    /**
     * Add title pattern filter
     */
    addTitlePattern(pattern, isRegex = false) {
        if (!pattern.trim()) return;

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

        console.log('SettingsPanel: Added title pattern:', pattern);
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
     * Detect current layout
     */
    detectLayout() {
        // Look for layout indicators in DOM or URL
        const body = document.body;
        if (body.classList.contains('layout-3x4')) return '3x4';
        if (body.classList.contains('layout-4x8')) return '4x8';
        if (body.classList.contains('layout-whats-next-view')) return 'whats-next-view';
        
        // Check URL path
        const path = window.location.pathname;
        if (path.includes('3x4')) return '3x4';
        if (path.includes('4x8')) return '4x8';
        if (path.includes('whats-next-view')) return 'whats-next-view';
        
        return 'unknown';
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
        
        console.log('SettingsPanel: Updated responsive layout for screen size:', this.screenSize);
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
        console.log('SettingsPanel: Cleanup completed');
    }
}

// Export for module systems or global use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsPanel;
} else if (typeof window !== 'undefined') {
    window.SettingsPanel = SettingsPanel;
}