/**
 * Debug script for settings panel accessibility focus management
 * 
 * This script patches the SettingsPanel close method to add detailed logging
 * around focus management and aria-hidden attribute changes to validate
 * the accessibility error diagnosis.
 */

(function() {
    'use strict';
    
    console.log('=== ACCESSIBILITY FOCUS DEBUG SCRIPT LOADED ===');
    
    // Store original console methods to avoid infinite loops
    const originalLog = console.log;
    const originalWarn = console.warn;
    const originalError = console.error;
    
    function debugLog(message, data = null) {
        originalLog(`[FOCUS-DEBUG] ${message}`, data || '');
    }
    
    function debugWarn(message, data = null) {
        originalWarn(`[FOCUS-DEBUG] ${message}`, data || '');
    }
    
    function debugError(message, data = null) {
        originalError(`[FOCUS-DEBUG] ${message}`, data || '');
    }
    
    // Helper to get detailed element info
    function getElementInfo(element) {
        if (!element) return 'null';
        return {
            tagName: element.tagName,
            className: element.className,
            id: element.id,
            ariaHidden: element.getAttribute('aria-hidden'),
            tabIndex: element.tabIndex,
            hasFocus: document.activeElement === element
        };
    }
    
    // Monitor focus changes
    let focusHistory = [];
    function trackFocus(event) {
        const activeEl = document.activeElement;
        const info = getElementInfo(activeEl);
        focusHistory.push({
            timestamp: Date.now(),
            event: event.type,
            element: info,
            target: event.target ? getElementInfo(event.target) : null
        });
        
        if (focusHistory.length > 10) {
            focusHistory.shift(); // Keep only last 10 events
        }
        
        debugLog(`Focus ${event.type}:`, info);
    }
    
    // Add focus tracking
    document.addEventListener('focusin', trackFocus);
    document.addEventListener('focusout', trackFocus);
    document.addEventListener('blur', trackFocus, true);
    document.addEventListener('focus', trackFocus, true);
    
    // Wait for SettingsPanel to be available and patch it
    function patchSettingsPanel() {
        if (typeof window.SettingsPanel === 'undefined') {
            debugWarn('SettingsPanel not yet available, retrying in 100ms');
            setTimeout(patchSettingsPanel, 100);
            return;
        }
        
        debugLog('SettingsPanel found, applying patches');
        
        // Store original methods
        const originalClose = window.SettingsPanel.prototype.close;
        const originalOpen = window.SettingsPanel.prototype.open;
        
        // Patch close method
        window.SettingsPanel.prototype.close = function() {
            debugLog('=== CLOSE METHOD CALLED ===');
            
            // Log initial state
            const panel = document.getElementById('settings-panel');
            const closeButton = panel ? panel.querySelector('.settings-close') : null;
            const activeElement = document.activeElement;
            
            debugLog('Initial state:', {
                isOpen: this.isOpen,
                isTransitioning: this.isTransitioning,
                panelExists: !!panel,
                closeButtonExists: !!closeButton,
                activeElement: getElementInfo(activeElement),
                panelAriaHidden: panel ? panel.getAttribute('aria-hidden') : 'no-panel'
            });
            
            debugLog('Focus history (last 10 events):', focusHistory);
            
            // Check if close button has focus
            if (closeButton && activeElement === closeButton) {
                debugError('ACCESSIBILITY ISSUE DETECTED: Close button has focus before aria-hidden is set!');
                debugLog('Close button info:', getElementInfo(closeButton));
            }
            
            // Monitor aria-hidden changes
            if (panel) {
                const observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'aria-hidden') {
                            const currentActive = document.activeElement;
                            debugLog('aria-hidden changed:', {
                                newValue: panel.getAttribute('aria-hidden'),
                                activeElement: getElementInfo(currentActive),
                                activeIsInPanel: panel.contains(currentActive)
                            });
                            
                            if (panel.getAttribute('aria-hidden') === 'true' && panel.contains(currentActive)) {
                                debugError('ACCESSIBILITY VIOLATION: aria-hidden=true set while descendant has focus!', {
                                    focusedElement: getElementInfo(currentActive)
                                });
                            }
                        }
                    });
                });
                
                observer.observe(panel, { attributes: true, attributeFilter: ['aria-hidden'] });
                
                // Clean up observer after 2 seconds
                setTimeout(() => observer.disconnect(), 2000);
            }
            
            // Call original method
            const result = originalClose.call(this);
            
            debugLog('=== CLOSE METHOD COMPLETED ===');
            debugLog('Final active element:', getElementInfo(document.activeElement));
            
            return result;
        };
        
        // Patch open method for comparison
        window.SettingsPanel.prototype.open = async function() {
            debugLog('=== OPEN METHOD CALLED ===');
            const result = await originalOpen.call(this);
            debugLog('Panel opened, focus set to:', getElementInfo(document.activeElement));
            return result;
        };
        
        debugLog('SettingsPanel methods patched successfully');
    }
    
    // Start patching
    patchSettingsPanel();
    
    // Add helper function to manually test focus management
    window.debugFocusState = function() {
        const panel = document.getElementById('settings-panel');
        const activeElement = document.activeElement;
        
        debugLog('Current focus state:', {
            activeElement: getElementInfo(activeElement),
            panelExists: !!panel,
            panelAriaHidden: panel ? panel.getAttribute('aria-hidden') : 'no-panel',
            panelOpen: panel ? panel.classList.contains('open') : false,
            focusHistory: focusHistory.slice(-5) // Last 5 events
        });
    };
    
    debugLog('Debug script initialization complete');
    debugLog('Use window.debugFocusState() to manually check focus state');
    
})();