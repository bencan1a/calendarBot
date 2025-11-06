/**
 * @fileoverview Phase 2 Jest Integration Tests - Component Interactions
 * Tests cross-component functionality, data flow, and system-wide interactions
 * Target: +20% Coverage focusing on component integration scenarios
 */

describe('Component Integration Tests', () => {
  let testSuite;
  let mockFetch;

  beforeEach(() => {
    // Create comprehensive test suite with all components
    testSuite = global.testUtils.createTestDataSuite();

    // Setup global fetch mock
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Setup localStorage mock
    Object.defineProperty(window, 'localStorage', {
      value: testSuite.localStorage,
      writable: true
    });

    // Setup DOM environment
    global.testUtils.setupMockDOM(`
      <div id="app">
        <div id="settings-panel" class="settings-panel" aria-hidden="true"></div>
        <div id="main-content">
          <div id="layout-container"></div>
          <div id="meeting-info"></div>
          <div id="theme-indicator"></div>
        </div>
      </div>
    `);
  });

  afterEach(() => {
    // Cleanup timers and event listeners
    testSuite.timers.stopAllTimers();
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  describe('Settings Panel and API Integration', () => {
    /**
     * Test the complete flow of opening settings panel, modifying settings,
     * and persisting changes through the API
     */
    describe('when managing settings through the panel', () => {
      it('should complete full settings modification workflow', async () => {
        // Setup API responses
        mockFetch
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse(testSuite.settings)) // Initial load
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ success: true })); // Save

        // Create integrated settings panel with API
        const settingsPanel = {
          isOpen: false,
          currentSettings: null,
          localSettings: null,
          hasUnsavedChanges: false,
          api: testSuite.apiClient,

          async initialize() {
            const result = await this.api.getSettings();
            if (result.success) {
              this.currentSettings = result.data;
              this.localSettings = JSON.parse(JSON.stringify(result.data));
            }
          },

          async open() {
            await this.initialize();
            this.isOpen = true;

            const panel = document.getElementById('settings-panel');
            panel.setAttribute('aria-hidden', 'false');
            panel.classList.add('open');
          },

          addTitlePattern(pattern) {
            if (!this.localSettings.event_filters) {
              this.localSettings.event_filters = { title_patterns: [] };
            }

            this.localSettings.event_filters.title_patterns.push({
              pattern,
              is_regex: false,
              is_active: true
            });

            this.hasUnsavedChanges = true;
          },

          async saveSettings() {
            const result = await this.api.updateSettings(this.localSettings);
            if (result.success) {
              this.currentSettings = JSON.parse(JSON.stringify(this.localSettings));
              this.hasUnsavedChanges = false;
              return true;
            }
            return false;
          }
        };

        // Execute workflow
        await settingsPanel.open();
        expect(settingsPanel.isOpen).toBe(true);
        expect(settingsPanel.currentSettings).toBeTruthy();

        // Modify settings
        settingsPanel.addTitlePattern('New Pattern');
        expect(settingsPanel.hasUnsavedChanges).toBe(true);
        expect(settingsPanel.localSettings.event_filters.title_patterns).toHaveLength(2);

        // Save changes
        const saveResult = await settingsPanel.saveSettings();
        expect(saveResult).toBe(true);
        expect(settingsPanel.hasUnsavedChanges).toBe(false);

        // Verify API calls
        expect(testSuite.apiClient.getSettings).toHaveBeenCalledTimes(1);
        expect(testSuite.apiClient.updateSettings).toHaveBeenCalledWith(
          expect.objectContaining({
            event_filters: expect.objectContaining({
              title_patterns: expect.arrayContaining([
                expect.objectContaining({ pattern: 'New Pattern' })
              ])
            })
          })
        );
      });

      it('should handle API failures gracefully in workflow', async () => {
        // Setup API failure
        testSuite.apiClient.getSettings.mockRejectedValueOnce(new Error('API failure'));

        const settingsPanel = {
          isOpen: false,
          error: null,
          api: testSuite.apiClient,

          async initialize() {
            try {
              await this.api.getSettings();
            } catch (error) {
              this.error = error.message;
              throw error;
            }
          },

          async open() {
            try {
              await this.initialize();
              this.isOpen = true;
            } catch (error) {
              this.isOpen = false;
              throw error;
            }
          }
        };

        // Attempt workflow with failure
        await expect(settingsPanel.open()).rejects.toThrow('API failure');
        expect(settingsPanel.isOpen).toBe(false);
        expect(settingsPanel.error).toBe('API failure');
      });
    });
  });

  describe('Navigation and Theme Integration', () => {
    /**
     * Test navigation between views with theme persistence
     * and component state management
     */
    describe('when navigating with theme changes', () => {
      it('should preserve theme across navigation', async () => {
        // Setup integrated navigation and theme manager
        const app = {
          navigation: testSuite.navigation,
          themeManager: testSuite.themeManager,
          currentLayout: '3x4',

          // Simulate app initialization
          async initialize() {
            // Load saved theme preference
            const savedTheme = testSuite.localStorage.getItem('preferred-theme');
            if (savedTheme) {
              this.themeManager.setTheme(savedTheme);
            }

            // Apply theme to DOM
            this.applyCurrentTheme();
          },

          applyCurrentTheme() {
            const theme = this.themeManager.currentTheme;
            document.body.setAttribute('data-theme', theme);

            const indicator = document.getElementById('theme-indicator');
            if (indicator) {
              indicator.textContent = `Current theme: ${theme}`;
            }
          },

          async changeTheme() {
            const newTheme = this.themeManager.toggleTheme();
            testSuite.localStorage.setItem('preferred-theme', newTheme);
            this.applyCurrentTheme();
            return newTheme;
          },

          navigateToSettings() {
            const success = this.navigation.navigate('settings');
            if (success) {
              // Update URL and DOM state
              const panel = document.getElementById('settings-panel');
              if (panel) {
                panel.setAttribute('aria-hidden', 'false');
              }
            }
            return success;
          }
        };

        // Initialize app
        await app.initialize();
        expect(app.themeManager.currentTheme).toBe('light');

        // Change theme
        const newTheme = await app.changeTheme();
        expect(newTheme).toBe('dark');
        expect(document.body.getAttribute('data-theme')).toBe('dark');
        expect(testSuite.localStorage.getItem('preferred-theme')).toBe('dark');

        // Navigate to settings
        const navSuccess = app.navigateToSettings();
        expect(navSuccess).toBe(true);
        expect(app.navigation.currentView).toBe('settings');

        // Verify theme persisted through navigation
        expect(app.themeManager.currentTheme).toBe('dark');
        expect(document.body.getAttribute('data-theme')).toBe('dark');

        // Simulate page reload - theme should persist
        await app.initialize();
        expect(app.themeManager.currentTheme).toBe('dark');
      });

      it('should handle navigation state restoration', () => {
        const app = {
          navigation: testSuite.navigation,
          history: [],

          saveNavigationState() {
            const state = {
              currentView: this.navigation.currentView,
              history: [...this.navigation.history]
            };
            testSuite.localStorage.setItem('navigation-state', JSON.stringify(state));
          },

          restoreNavigationState() {
            const saved = testSuite.localStorage.getItem('navigation-state');
            if (saved) {
              const state = JSON.parse(saved);
              this.navigation.currentView = state.currentView;
              this.navigation.history = state.history;
              return true;
            }
            return false;
          },

          navigateWithSave(target) {
            const success = this.navigation.navigate(target);
            if (success) {
              this.saveNavigationState();
            }
            return success;
          }
        };

        // Navigate through multiple views
        app.navigateWithSave('settings');
        app.navigateWithSave('about');

        expect(app.navigation.currentView).toBe('about');
        expect(app.navigation.history).toContain('main');
        expect(app.navigation.history).toContain('settings');

        // Simulate app restart
        const newApp = {
          navigation: testSuite.navigation,
          restoreNavigationState: app.restoreNavigationState
        };

        newApp.navigation.currentView = 'main';
        newApp.navigation.history = [];

        // Restore state
        const restored = newApp.restoreNavigationState();
        expect(restored).toBe(true);
        expect(newApp.navigation.currentView).toBe('about');
        expect(newApp.navigation.history).toContain('settings');
      });
    });
  });

  describe('Meeting Detection and Timer Integration', () => {
    /**
     * Test meeting detection with countdown timers and
     * component state synchronization
     */
    describe('when managing meeting timers and layout updates', () => {
      it('should coordinate meeting detection with UI updates', async () => {
        // Setup integrated meeting and timer system
        const meetingManager = {
          timers: testSuite.timers,
          currentMeeting: null,
          countdownTimer: null,
          events: testSuite.events,

          detectCurrentMeeting() {
            const now = new Date();

            // Find active meeting
            const activeMeeting = this.events.find(event => {
              const start = new Date(event.start);
              const end = new Date(event.end);
              return now >= start && now <= end;
            });

            if (activeMeeting) {
              this.currentMeeting = {
                ...activeMeeting,
                status: 'active',
                timeRemaining: new Date(activeMeeting.end) - now
              };

              this.startCountdown(new Date(activeMeeting.end));
              this.updateMeetingDisplay();
              return this.currentMeeting;
            }

            return null;
          },

          startCountdown(endTime) {
            this.countdownTimer = this.timers.createCountdown(endTime, () => {
              this.onCountdownComplete();
            });
          },

          stopCountdown() {
            if (this.countdownTimer) {
              this.timers.stopCountdown(this.countdownTimer);
              this.countdownTimer = null;
            }
          },

          onCountdownComplete() {
            // Clear current meeting and stop countdown
            if (this.countdownTimer) {
              this.timers.stopCountdown(this.countdownTimer);
              this.countdownTimer = null;
            }
            this.currentMeeting = null;
            this.updateMeetingDisplay();
            // Don't re-detect immediately - let the calling code decide
          },

          updateMeetingDisplay() {
            const meetingInfo = document.getElementById('meeting-info');
            if (meetingInfo) {
              if (this.currentMeeting) {
                meetingInfo.innerHTML = `
                  <div class="current-meeting">
                    <h3>${this.currentMeeting.title}</h3>
                    <p>Status: ${this.currentMeeting.status}</p>
                    <div id="countdown-display"></div>
                  </div>
                `;
              } else {
                meetingInfo.innerHTML = '<div class="no-meeting">No active meeting</div>';
              }
            }
          }
        };

        // Setup events with one active meeting
        const now = new Date();
        const activeMeeting = {
          id: 'active-1',
          title: 'Current Meeting',
          start: new Date(now.getTime() - 10 * 60 * 1000).toISOString(), // Started 10 mins ago
          end: new Date(now.getTime() + 20 * 60 * 1000).toISOString()    // Ends in 20 mins
        };

        meetingManager.events = [activeMeeting];

        // Detect meeting
        const detected = meetingManager.detectCurrentMeeting();

        expect(detected).toBeTruthy();
        expect(detected.title).toBe('Current Meeting');
        expect(detected.status).toBe('active');
        expect(meetingManager.countdownTimer).toBeTruthy();

        // Verify UI update
        const meetingInfo = document.getElementById('meeting-info');
        expect(meetingInfo.innerHTML).toContain('Current Meeting');
        expect(meetingInfo.innerHTML).toContain('Status: active');

        // Verify timer was created
        expect(meetingManager.timers.getActiveTimerCount()).toBe(1);

        // Simulate meeting end by moving time forward beyond meeting end
        const pastMeetingEnd = new Date(now.getTime() + 25 * 60 * 1000); // 5 mins after meeting ends
        const originalDateNow = Date.now;
        global.Date.now = jest.fn(() => pastMeetingEnd.getTime());

        // Simulate countdown completion
        meetingManager.onCountdownComplete();

        expect(meetingManager.currentMeeting).toBeNull();
        expect(meetingInfo.innerHTML).toContain('No active meeting');

        // Restore Date.now
        global.Date.now = originalDateNow;
      });

      it('should handle timer cleanup during component destruction', () => {
        const component = {
          timers: testSuite.timers,
          activeTimers: [],
          isDestroyed: false,

          createTimer(endTime, callback) {
            const timerId = this.timers.createCountdown(endTime, callback);
            this.activeTimers.push(timerId);
            return timerId;
          },

          destroy() {
            // Cleanup all timers
            this.activeTimers.forEach(timerId => {
              this.timers.stopCountdown(timerId);
            });
            this.activeTimers = [];
            this.isDestroyed = true;
          }
        };

        // Create multiple timers
        const timer1 = component.createTimer(new Date(Date.now() + 60000), () => {});
        const timer2 = component.createTimer(new Date(Date.now() + 120000), () => {});

        expect(component.activeTimers).toHaveLength(2);
        expect(component.timers.getActiveTimerCount()).toBe(2);

        // Destroy component
        component.destroy();

        expect(component.activeTimers).toHaveLength(0);
        expect(component.timers.getActiveTimerCount()).toBe(0);
        expect(component.isDestroyed).toBe(true);
      });
    });
  });

  describe('Layout Cycling and State Persistence', () => {
    /**
     * Test layout switching with state preservation
     * and responsive behavior
     */
    describe('when cycling layouts with state management', () => {
      it('should preserve component state across layout changes', () => {
        // Setup layout manager with state persistence
        const layoutManager = {
          currentLayout: '3x4',
          availableLayouts: ['3x4', 'whats-next', 'grid'],
          componentStates: new Map(),
          localStorage: testSuite.localStorage,

          saveComponentState(componentName, state) {
            this.componentStates.set(componentName, state);
            this.localStorage.setItem('component-states',
              JSON.stringify(Object.fromEntries(this.componentStates))
            );
          },

          restoreComponentState(componentName) {
            // First try in-memory cache
            if (this.componentStates.has(componentName)) {
              return this.componentStates.get(componentName);
            }

            // Then try localStorage
            const saved = this.localStorage.getItem('component-states');
            if (saved) {
              const states = JSON.parse(saved);
              if (states[componentName]) {
                this.componentStates.set(componentName, states[componentName]);
                return states[componentName];
              }
            }

            return null;
          },

          cycleLayout() {
            const currentIndex = this.availableLayouts.indexOf(this.currentLayout);
            const nextIndex = (currentIndex + 1) % this.availableLayouts.length;
            const newLayout = this.availableLayouts[nextIndex];

            // Save current layout preference
            this.localStorage.setItem('preferred-layout', newLayout);

            // Update current layout
            const previousLayout = this.currentLayout;
            this.currentLayout = newLayout;

            return { previousLayout, newLayout };
          }
        };

        // Create mock component with state
        const settingsComponent = {
          name: 'settings-panel',
          isOpen: false,
          filters: ['pattern1', 'pattern2'],

          getState() {
            return {
              isOpen: this.isOpen,
              filters: [...this.filters]
            };
          },

          setState(state) {
            this.isOpen = state.isOpen || false;
            this.filters = state.filters || [];
          }
        };

        // Save component state
        settingsComponent.isOpen = true;
        settingsComponent.filters.push('pattern3');

        layoutManager.saveComponentState(settingsComponent.name, settingsComponent.getState());

        // Cycle layout
        const { previousLayout, newLayout } = layoutManager.cycleLayout();
        expect(previousLayout).toBe('3x4');
        expect(newLayout).toBe('whats-next');
        expect(layoutManager.localStorage.getItem('preferred-layout')).toBe('whats-next');

        // Create new component instance (simulating layout change)
        const newSettingsComponent = {
          name: 'settings-panel',
          isOpen: false,
          filters: [],

          getState() {
            return {
              isOpen: this.isOpen,
              filters: [...this.filters]
            };
          },

          setState(state) {
            this.isOpen = state.isOpen || false;
            this.filters = state.filters || [];
          }
        };

        // Restore state
        const restoredState = layoutManager.restoreComponentState(newSettingsComponent.name);
        expect(restoredState).toBeTruthy();

        newSettingsComponent.setState(restoredState);
        expect(newSettingsComponent.isOpen).toBe(true);
        expect(newSettingsComponent.filters).toContain('pattern3');
      });
    });
  });

  describe('Error Propagation and Recovery', () => {
    /**
     * Test error handling across component boundaries
     * and system-wide error recovery
     */
    describe('when handling cross-component errors', () => {
      it('should propagate and handle errors across component boundaries', async () => {
        const errorManager = {
          errors: [],
          components: new Map(),

          registerComponent(name, component) {
            this.components.set(name, component);
          },

          handleError(error, componentName) {
            const errorInfo = {
              error: error.message,
              component: componentName,
              timestamp: new Date(),
              recovered: false
            };

            this.errors.push(errorInfo);

            // Attempt recovery
            const component = this.components.get(componentName);
            if (component && component.recover) {
              try {
                component.recover();
                errorInfo.recovered = true;
              } catch (recoveryError) {
                errorInfo.recoveryError = recoveryError.message;
              }
            }

            return errorInfo;
          },

          getErrorCount() {
            return this.errors.length;
          },

          getRecoveredCount() {
            return this.errors.filter(e => e.recovered).length;
          }
        };

        // Create components with error handling
        const apiComponent = {
          name: 'api-client',
          isHealthy: true,

          async failingOperation() {
            this.isHealthy = false;
            throw new Error('API connection failed');
          },

          recover() {
            this.isHealthy = true;
            console.log('API component recovered');
          }
        };

        const uiComponent = {
          name: 'ui-manager',
          isHealthy: true,

          async dependentOperation() {
            // This operation depends on API
            try {
              await apiComponent.failingOperation();
            } catch (error) {
              this.isHealthy = false;
              throw new Error(`UI operation failed: ${error.message}`);
            }
          },

          recover() {
            this.isHealthy = true;
            console.log('UI component recovered');
          }
        };

        // Register components
        errorManager.registerComponent(apiComponent.name, apiComponent);
        errorManager.registerComponent(uiComponent.name, uiComponent);

        // Trigger cascading failure
        try {
          await uiComponent.dependentOperation();
        } catch (error) {
          errorManager.handleError(error, uiComponent.name);
        }

        // Should have recorded UI error but not API error yet
        expect(errorManager.getErrorCount()).toBe(1);
        expect(errorManager.errors[0].component).toBe('ui-manager');

        // Trigger API error handling
        try {
          await apiComponent.failingOperation();
        } catch (error) {
          errorManager.handleError(error, apiComponent.name);
        }

        // Now should have both errors
        expect(errorManager.getErrorCount()).toBe(2);

        // Check recovery
        const recoveredCount = errorManager.getRecoveredCount();
        expect(recoveredCount).toBe(2); // Both components should recover

        expect(apiComponent.isHealthy).toBe(true);
        expect(uiComponent.isHealthy).toBe(true);
      });
    });
  });
});