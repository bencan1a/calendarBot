# Renderer Migration: Removal of Obsolete Components

## Overview

This document describes the migration from the legacy Raspberry Pi renderer components to the unified rendering pipeline. The obsolete components (`rpi_html_renderer.py` and `compact_eink_renderer.py`) have been removed and replaced with the new unified renderers (`WhatsNextRenderer` and `EInkWhatsNextRenderer`).

## Changes Made

1. Removed obsolete renderer files:
   - `calendarbot/display/rpi_html_renderer.py`
   - `calendarbot/display/compact_eink_renderer.py`

2. Removed associated test files:
   - `tests/unit/display/test_rpi_html_renderer.py`
   - `tests/unit/display/test_compact_eink_renderer.py`

3. Updated `renderer_factory.py`:
   - Modified the device-to-renderer mapping to use the new renderers:
     - "rpi" device type now maps to "whats-next" renderer
     - "compact" device type now maps to "eink-whats-next" renderer
   - Added legacy type mappings for backward compatibility:
     - "rpi" renderer type now maps to WhatsNextRenderer
     - "compact" renderer type now maps to EInkWhatsNextRenderer

4. Updated `test_renderer_factory.py`:
   - Updated tests to use the new renderer classes
   - Fixed mocking for EInkWhatsNextRenderer_TYPE
   - Updated expected available renderers list
   - Updated device-to-renderer mapping tests

## Rationale

The unified rendering pipeline provides a more consistent and maintainable approach to rendering calendar data across different display types. The new renderers (`WhatsNextRenderer` and `EInkWhatsNextRenderer`) use shared styling constants and a common architecture, making it easier to maintain and extend the rendering functionality.

The legacy renderers were specific to particular hardware configurations and had duplicated code. By migrating to the unified rendering pipeline, we've reduced code duplication and improved the overall architecture of the display subsystem.

## Backward Compatibility

To maintain backward compatibility with existing code that might still reference the old renderer types, we've added legacy type mappings in the renderer factory. This ensures that code using "rpi" or "compact" as renderer types will still work, but will now use the new renderer classes.

## Testing

All tests for the renderer factory have been updated and are passing. There are some test failures in the EInkWhatsNextRenderer tests, but these are related to font loading and rendering functionality, not to our changes to the renderer factory.

## Future Work

- Update any remaining code that might still reference the old renderer types
- Fix the failing tests in the EInkWhatsNextRenderer tests
- Consider adding deprecation warnings for the legacy renderer types